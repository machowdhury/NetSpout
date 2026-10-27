"""
Run Progress Tracking System
Tracks per-run progress events with WebSocket broadcasting.
"""

import asyncio
from datetime import datetime
from enum import Enum
import json
from typing import Dict, List, Optional, Any
import uuid
import time


class RunProgressState(str, Enum):
    """Progress states for a scenario run."""
    QUEUED = "QUEUED"
    PREPARING = "PREPARING"
    GENERATING = "GENERATING"
    SENDING = "SENDING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RunProgressEvent:
    """Single progress event for a run."""
    
    def __init__(
        self,
        run_id: str,
        state: RunProgressState,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        self.event_id = str(uuid.uuid4())
        self.run_id = run_id
        self.state = state
        self.timestamp = datetime.now()
        self.message = message
        self.details = details or {}
        
        # Progress metrics
        self.current_phase = kwargs.get('current_phase')
        self.phases_total = kwargs.get('phases_total')
        self.phases_completed = kwargs.get('phases_completed')
        
        # Counters
        self.generated_count = kwargs.get('generated_count')
        self.accepted_count = kwargs.get('accepted_count')
        self.rejected_count = kwargs.get('rejected_count')
        self.indexed_count = kwargs.get('indexed_count')
        self.verified_count = kwargs.get('verified_count')
        
        # Transport metrics
        self.transport_target = kwargs.get('transport_target')
        self.transport_protocol = kwargs.get('transport_protocol')
        self.transport_status = kwargs.get('transport_status')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_id": self.event_id,
            "run_id": self.run_id,
            "state": self.state.value if isinstance(self.state, Enum) else self.state,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "details": self.details,
            "current_phase": self.current_phase,
            "phases_total": self.phases_total,
            "phases_completed": self.phases_completed,
            "generated_count": self.generated_count,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "indexed_count": self.indexed_count,
            "verified_count": self.verified_count,
            "transport_target": self.transport_target,
            "transport_protocol": self.transport_protocol,
            "transport_status": self.transport_status
        }


class RunProgressTracker:
    """Tracks progress for multiple concurrent runs."""
    
    def __init__(self, broadcast_callback=None):
        """
        Args:
            broadcast_callback: Async function to call when progress updates
        """
        self.active_runs: Dict[str, RunProgressEvent] = {}
        self.run_history: Dict[str, List[RunProgressEvent]] = {}
        self.broadcast_callback = broadcast_callback
    
    def start_run(self, run_id: str, scenario_id: str) -> RunProgressEvent:
        """Initialize tracking for a new run."""
        event = RunProgressEvent(
            run_id=run_id,
            state=RunProgressState.QUEUED,
            message=f"Run {run_id} queued for scenario {scenario_id}",
            details={"scenario_id": scenario_id}
        )
        self.active_runs[run_id] = event
        self.run_history[run_id] = [event]
        
        # Broadcast initial state
        if self.broadcast_callback:
            asyncio.create_task(self.broadcast_callback(event))
        
        return event
    
    def update_run_state(
        self,
        run_id: str,
        state: RunProgressState,
        message: str,
        **details
    ) -> Optional[RunProgressEvent]:
        """Update the state of a run."""
        if run_id not in self.active_runs:
            return None
        
        current = self.active_runs[run_id]
        
        # Merge details
        merged_details = {**current.details, **details}
        
        # Create new event
        event = RunProgressEvent(
            run_id=run_id,
            state=state,
            message=message,
            details=merged_details,
            current_phase=details.get('current_phase', current.current_phase),
            phases_total=details.get('phases_total', current.phases_total),
            phases_completed=details.get('phases_completed', current.phases_completed),
            generated_count=details.get('generated_count', current.generated_count),
            accepted_count=details.get('accepted_count', current.accepted_count),
            rejected_count=details.get('rejected_count', current.rejected_count),
            indexed_count=details.get('indexed_count', current.indexed_count),
            verified_count=details.get('verified_count', current.verified_count),
            transport_target=details.get('transport_target', current.transport_target),
            transport_protocol=details.get('transport_protocol', current.transport_protocol),
            transport_status=details.get('transport_status', current.transport_status)
        )
        
        self.active_runs[run_id] = event
        self.run_history[run_id].append(event)
        
        # Broadcast update
        if self.broadcast_callback:
            asyncio.create_task(self.broadcast_callback(event))
        
        return event
    
    def complete_run(self, run_id: str, success: bool = True, **details) -> Optional[RunProgressEvent]:
        """Mark a run as completed."""
        if run_id not in self.active_runs:
            return None
        
        state = RunProgressState.COMPLETED if success else RunProgressState.FAILED
        message = f"Run {run_id} {'completed successfully' if success else 'failed'}"
        
        event = self.update_run_state(
            run_id,
            state,
            message,
            **details
        )
        
        # Keep run in active runs for a short time (for verification queries)
        # but schedule removal
        if success:
            asyncio.create_task(self._remove_run_after_delay(run_id, delay=60))
        
        return event
    
    def cancel_run(self, run_id: str, reason: str = "User requested cancellation") -> Optional[RunProgressEvent]:
        """Cancel a run."""
        if run_id not in self.active_runs:
            return None
        
        event = self.update_run_state(
            run_id,
            RunProgressState.CANCELLED,
            f"Run {run_id} cancelled: {reason}",
            cancellation_reason=reason
        )
        
        # Remove immediately
        self.active_runs.pop(run_id, None)
        
        return event
    
    def get_run_progress(self, run_id: str) -> Optional[RunProgressEvent]:
        """Get current progress for a run."""
        return self.active_runs.get(run_id)
    
    def get_run_history(self, run_id: str) -> List[RunProgressEvent]:
        """Get history of progress events for a run."""
        return self.run_history.get(run_id, [])
    
    def get_all_active_runs(self) -> Dict[str, RunProgressEvent]:
        """Get all active runs."""
        return self.active_runs.copy()
    
    async def _remove_run_after_delay(self, run_id: str, delay: int = 60):
        """Remove a run from active tracking after delay."""
        await asyncio.sleep(delay)
        self.active_runs.pop(run_id, None)


# Global instance
progress_tracker = RunProgressTracker()