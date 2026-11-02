"""
Unified Splunk Destination Manager for PulseForge.

Provides complete destination management for both Docker-based and external Splunk instances.
"""
import json
import os
import time
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator
from urllib.parse import urlsplit
import ipaddress
import httpx

from app.models import TelemetryTransportConfig, DEFAULT_SPLUNK_HEC_URL

class SplunkDeploymentType(str, Enum):
    DOCKER_LOCAL = "docker_local"
    DOCKER_COMPOSE = "docker_compose"
    EXTERNAL_CLOUD = "external_cloud"
    EXTERNAL_ENTERPRISE = "external_enterprise"
    SPLUNK_CLOUD = "splunk_cloud"

class SplunkDestination(BaseModel):
    """Unified Splunk destination configuration."""
    id: str = Field(description="Unique identifier for this destination")
    name: str = Field(description="Display name")
    deployment_type: SplunkDeploymentType
    enabled: bool = True

    # Connection details
    hec_url: str = DEFAULT_SPLUNK_HEC_URL
    hec_token: Optional[str] = Field(default=None, exclude=True)
    search_url: Optional[str] = None
    search_username: Optional[str] = None
    search_password: Optional[str] = Field(default=None, exclude=True)

    # Docker-specific settings
    docker_container: Optional[str] = None
    docker_compose_file: Optional[str] = None

    hec_index: str = "idx_network_ops"
    hec_metric_index: str = "cisco_mdt_metrics"
    hec_ssl_verify: bool = True
    hec_allow_insecure_tls: bool = False
    hec_token_env: Optional[str] = None

    # Validation status
    last_validated: Optional[float] = None
    validation_status: str = "unknown"  # unknown, valid, invalid, testing
    validation_message: Optional[str] = None

    # Usage statistics
    total_events_sent: int = 0
    last_used: Optional[float] = None

    @field_validator("hec_url", "search_url")
    @classmethod
    def validate_url(cls, value):
        if value is None:
            return value
        parsed = urlsplit(value)
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Destination URLs cannot contain credentials, queries or fragments")
        if not parsed.hostname or parsed.scheme not in ("https", "http"):
            raise ValueError("Destination requires an HTTP(S) URL")
        if parsed.scheme == "http":
            try:
                local = ipaddress.ip_address(parsed.hostname).is_loopback
            except ValueError:
                local = parsed.hostname == "localhost"
            if not local:
                raise ValueError("External destinations require HTTPS")
        return value

    def to_transport_config(self) -> TelemetryTransportConfig:
        """Convert to TelemetryTransportConfig for use with dispatcher."""
        return TelemetryTransportConfig(
            hec_enabled=self.enabled,
            hec_url=self.hec_url,
            hec_token=self.hec_token or os.environ.get(self.hec_token_env or "", ""),
            hec_index=self.hec_index,
            hec_metric_index=self.hec_metric_index,
            hec_ssl_verify=self.hec_ssl_verify,
            hec_allow_insecure_tls=self.hec_allow_insecure_tls,
        )

    def mask_secrets(self) -> 'SplunkDestination':
        """Return a copy with secrets masked for UI display."""
        return self.model_copy(update={"hec_token": None, "search_password": None})

class DestinationTestResult(BaseModel):
    """Result of destination connection test."""
    success: bool
    message: str
    details: Dict[str, Any]
    response_time_ms: Optional[float] = None
    endpoints_tested: List[str] = []

class DestinationManager:
    """Manages Splunk destinations with Docker and external support."""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or self._default_config_file()
        self.destinations: Dict[str, SplunkDestination] = {}
        self.active_destination_id: Optional[str] = None
        self.load_destinations()

    @staticmethod
    def _default_config_file() -> str:
        """Resolve the destinations file location-independent.

        A bare relative path made the active destination depend on the
        process CWD, so running from the repo root silently loaded a stale
        copy (with a metric index the HEC token does not allow). Anchor to
        this module's backend/ directory unless an explicit override is set.
        """
        override = os.environ.get("PULSEFORGE_DESTINATIONS_FILE")
        if override:
            return override
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(backend_dir, "destinations.json")

    def load_destinations(self):
        """Load destinations from config file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    for dest_id, dest_data in data.get('destinations', {}).items():
                        self.destinations[dest_id] = SplunkDestination(**dest_data)
                    self.active_destination_id = data.get('active_destination_id')

                # If no destinations loaded, create defaults
                if not self.destinations:
                    self.create_default_destinations()
            else:
                # Config file doesn't exist, create defaults
                self.create_default_destinations()
        except Exception as e:
            print(f"Warning: Could not load destinations: {e}")
            # Create default Docker destination
            self.create_default_destinations()

    def save_destinations(self):
        """Save destinations to config file."""
        try:
            data = {
                'destinations': {
                    dest_id: dest.model_dump(exclude={'hec_token', 'search_password'})
                    for dest_id, dest in self.destinations.items()
                },
                'active_destination_id': self.active_destination_id
            }
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving destinations: {e}")

    def create_default_destinations(self):
        """Create default destinations if none exist."""
        # Docker local destination
        docker_dest = SplunkDestination(
            id="docker_local",
            name="Local Docker Splunk",
            deployment_type=SplunkDeploymentType.DOCKER_LOCAL,
            hec_url="https://localhost:8088/services/collector",
            docker_container="splunk",
            validation_status="unknown"
        )
        self.destinations[docker_dest.id] = docker_dest

        # Default external destination
        external_dest = SplunkDestination(
            id="external_default",
            name="External Splunk (Edit Me)",
            deployment_type=SplunkDeploymentType.EXTERNAL_ENTERPRISE,
            hec_url="https://splunk.example.com:8088/services/collector",
            validation_status="unknown"
        )
        self.destinations[external_dest.id] = external_dest

        self.active_destination_id = docker_dest.id
        self.save_destinations()

    def add_destination(self, destination: SplunkDestination) -> str:
        """Add a new destination."""
        if destination.id in self.destinations:
            # Generate unique ID
            base_id = destination.id
            counter = 1
            while f"{base_id}_{counter}" in self.destinations:
                counter += 1
            destination.id = f"{base_id}_{counter}"

        self.destinations[destination.id] = destination
        self.save_destinations()
        return destination.id

    def update_destination(self, dest_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing destination."""
        if dest_id not in self.destinations:
            return False

        current = self.destinations[dest_id]
        updated_data = current.model_dump()
        updated_data.update(updates)

        # Preserve secrets if not provided in updates
        if 'hec_token' not in updates or updates['hec_token'] == "***MASKED***":
            updated_data['hec_token'] = current.hec_token
        if 'search_password' not in updates or updates['search_password'] == "***MASKED***":
            updated_data['search_password'] = current.search_password

        self.destinations[dest_id] = SplunkDestination(**updated_data)
        self.save_destinations()
        return True

    def delete_destination(self, dest_id: str) -> bool:
        """Delete a destination."""
        if dest_id not in self.destinations:
            return False

        del self.destinations[dest_id]

        # If deleting active destination, pick another
        if self.active_destination_id == dest_id:
            self.active_destination_id = next(iter(self.destinations.keys())) if self.destinations else None

        self.save_destinations()
        return True

    def set_active_destination(self, dest_id: str) -> bool:
        """Set the active destination for scenario execution."""
        if dest_id not in self.destinations:
            return False

        self.active_destination_id = dest_id
        self.save_destinations()
        return True

    def get_active_destination(self) -> Optional[SplunkDestination]:
        """Get the active destination."""
        if not self.active_destination_id:
            return None
        return self.destinations.get(self.active_destination_id)

    def get_active_transport_config(self) -> Optional[TelemetryTransportConfig]:
        """Get TelemetryTransportConfig for active destination."""
        dest = self.get_active_destination()
        if not dest:
            return None
        return dest.to_transport_config()

    async def test_destination(self, dest_id: str) -> DestinationTestResult:
        dest = self.destinations.get(dest_id)
        if dest is None:
            return DestinationTestResult(success=False, message="Destination not found", details={})
        transport = dest.to_transport_config()
        if not dest.enabled or not transport.hec_token:
            return DestinationTestResult(success=False, message="Destination disabled or HEC credential unavailable", details={})
        start = time.monotonic()
        try:
            # Authenticated health probe; does not submit synthetic events.
            url = dest.hec_url.split("/services/collector")[0] + "/services/collector/health"
            async with httpx.AsyncClient(verify=dest.hec_ssl_verify and not dest.hec_allow_insecure_tls, timeout=5, trust_env=False) as client:
                response = await client.get(url, headers={"Authorization": "Splunk " + transport.hec_token})
            ok = response.status_code == 200 and response.json().get("code") in (0, 17)
            message = "HEC health reachable; token ingestion and search permissions not verified" if ok else f"HEC health HTTP {response.status_code}"
            dest.validation_status = "health_reachable" if ok else "invalid"
        except Exception:
            ok, message = False, "HEC connection failed (TLS, network or invalid response)"
            dest.validation_status = "invalid"
        dest.validation_message = message
        dest.last_validated = time.time()
        self.save_destinations()
        return DestinationTestResult(success=ok, message=message, details={"search_permissions_verified": False, "ingestion_verified": False}, response_time_ms=(time.monotonic()-start)*1000, endpoints_tested=["hec_health"])

    def record_event_sent(self, dest_id: str, count: int = 1):
        dest = self.destinations[dest_id]
        dest.total_events_sent += count
        dest.last_used = time.time()
        self.save_destinations()

    def get_destination_stats(self, dest_id: str):
        dest = self.destinations[dest_id]
        return {"total_events_sent": dest.total_events_sent, "last_used": dest.last_used}


destination_manager = DestinationManager()
