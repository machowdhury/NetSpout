"""
API endpoints for unified Splunk destination management.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
import time

from app.destination_manager import (
    destination_manager, SplunkDestination, SplunkDeploymentType,
    DestinationTestResult
)
from app.models import TelemetryTransportConfig

router = APIRouter(prefix="/api/destinations", tags=["destinations"])

@router.get("/", response_model=List[Dict[str, Any]])
async def list_destinations():
    """List all configured destinations."""
    destinations = []
    for dest_id, dest in destination_manager.destinations.items():
        dest_dict = dest.mask_secrets().model_dump()
        dest_dict["is_active"] = (dest_id == destination_manager.active_destination_id)
        dest_dict["stats"] = destination_manager.get_destination_stats(dest_id)
        destinations.append(dest_dict)

    return destinations

@router.get("/active", response_model=Optional[Dict[str, Any]])
async def get_active_destination():
    """Get the active destination."""
    active_dest = destination_manager.get_active_destination()
    if not active_dest:
        return None

    result = active_dest.mask_secrets().model_dump()
    result["transport_config"] = active_dest.to_transport_config().model_dump()
    return result

@router.post("/active/{dest_id}")
async def set_active_destination(dest_id: str):
    """Set the active destination for scenario execution."""
    success = destination_manager.set_active_destination(dest_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Destination not found: {dest_id}")

    return {"status": "success", "active_destination_id": dest_id}

@router.get("/deployment-types", response_model=List[Dict[str, Any]])
async def get_deployment_types():
    """Get available deployment types with descriptions."""
    return [
        {
            "id": SplunkDeploymentType.DOCKER_LOCAL,
            "name": "Local Docker Container",
            "description": "Splunk running in a local Docker container",
            "requires_docker": True,
            "requires_credentials": False
        },
        {
            "id": SplunkDeploymentType.DOCKER_COMPOSE,
            "name": "Docker Compose",
            "description": "Splunk defined in a docker-compose.yml file",
            "requires_docker": True,
            "requires_credentials": False
        },
        {
            "id": SplunkDeploymentType.EXTERNAL_CLOUD,
            "name": "External Cloud Instance",
            "description": "Splunk Cloud or cloud-hosted Splunk instance",
            "requires_docker": False,
            "requires_credentials": True
        },
        {
            "id": SplunkDeploymentType.EXTERNAL_ENTERPRISE,
            "name": "External Enterprise Instance",
            "description": "On-premises or enterprise Splunk deployment",
            "requires_docker": False,
            "requires_credentials": True
        },
        {
            "id": SplunkDeploymentType.SPLUNK_CLOUD,
            "name": "Splunk Cloud",
            "description": "Official Splunk Cloud service",
            "requires_docker": False,
            "requires_credentials": True
        }
    ]


@router.get("/{dest_id}", response_model=Dict[str, Any])
async def get_destination(dest_id: str):
    """Get a specific destination."""
    if dest_id not in destination_manager.destinations:
        raise HTTPException(status_code=404, detail=f"Destination not found: {dest_id}")

    dest = destination_manager.destinations[dest_id]
    result = dest.mask_secrets().model_dump()
    result["is_active"] = (dest_id == destination_manager.active_destination_id)
    result["stats"] = destination_manager.get_destination_stats(dest_id)
    return result

@router.post("/", response_model=Dict[str, Any])
async def create_destination(destination: SplunkDestination):
    """Create a new destination."""
    dest_id = destination_manager.add_destination(destination)

    # Set as active if it's the first destination
    if len(destination_manager.destinations) == 1:
        destination_manager.set_active_destination(dest_id)

    return {
        "status": "created",
        "destination_id": dest_id,
        "destination": destination.mask_secrets().model_dump()
    }

@router.put("/{dest_id}", response_model=Dict[str, Any])
async def update_destination(dest_id: str, updates: Dict[str, Any]):
    """Update an existing destination."""
    success = destination_manager.update_destination(dest_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail=f"Destination not found: {dest_id}")

    dest = destination_manager.destinations[dest_id]
    return {
        "status": "updated",
        "destination_id": dest_id,
        "destination": dest.mask_secrets().model_dump()
    }

@router.delete("/{dest_id}")
async def delete_destination(dest_id: str):
    """Delete a destination."""
    success = destination_manager.delete_destination(dest_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Destination not found: {dest_id}")

    return {"status": "deleted", "destination_id": dest_id}

@router.post("/{dest_id}/test", response_model=DestinationTestResult)
async def test_destination(dest_id: str):
    """Test connection to a destination."""
    if dest_id not in destination_manager.destinations:
        raise HTTPException(status_code=404, detail=f"Destination not found: {dest_id}")

    result = await destination_manager.test_destination(dest_id)
    return result

@router.post("/test-connection")
async def test_connection_direct(destination: SplunkDestination):
    """Test connection to a destination without saving it."""
    # Create temporary destination for testing
    temp_id = f"temp_test_{int(time.time())}"
    destination.id = temp_id

    # Test the connection
    destination_manager.destinations[temp_id] = destination
    try:
        result = await destination_manager.test_destination(temp_id)
    finally:
        destination_manager.destinations.pop(temp_id, None)
        destination_manager.save_destinations()

    # Don't save the temporary destination
    if temp_id in destination_manager.destinations:
        del destination_manager.destinations[temp_id]

    return result

@router.get("/{dest_id}/transport-config", response_model=TelemetryTransportConfig)
async def get_destination_transport_config(dest_id: str):
    """Get TelemetryTransportConfig for a destination."""
    if dest_id == "active":
        dest_id = destination_manager.active_destination_id
    if dest_id not in destination_manager.destinations:
        raise HTTPException(status_code=404, detail=f"Destination not found: {dest_id}")

    dest = destination_manager.destinations[dest_id]
    return dest.to_transport_config()

@router.post("/{dest_id}/record-events")
async def record_events_sent(dest_id: str, count: int = 1):
    """Record that events were sent to a destination."""
    if dest_id not in destination_manager.destinations:
        raise HTTPException(status_code=404, detail=f"Destination not found: {dest_id}")

    destination_manager.record_event_sent(dest_id, count)
    return {"status": "recorded", "event_count": count}

@router.get("/{dest_id}/stats", response_model=Dict[str, Any])
async def get_destination_statistics(dest_id: str):
    """Get statistics for a destination."""
    if dest_id not in destination_manager.destinations:
        raise HTTPException(status_code=404, detail=f"Destination not found: {dest_id}")

    return destination_manager.get_destination_stats(dest_id)
