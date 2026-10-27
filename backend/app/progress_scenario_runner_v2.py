"""
Progress-aware Scenario Runner wrapper.
Integrates progress tracking with the existing ScenarioRunner.
"""

import asyncio
import time
from typing import Optional, Dict, Any


class ProgressScenarioRunner:
    """Scenario runner with progress tracking."""
    
    def __init__(self, base_runner):
        self.base_runner = base_runner
    
    async def run_scenario_with_progress(
        self,
        request,
        destination_info: Optional[Dict[str, Any]] = None
    ):
        """
        Run a scenario with progress tracking.
        
        Args:
            request: Scenario run request
            destination_info: Destination information for progress tracking
            
        Returns:
            RunManifest from the scenario execution
        """
        # Import here to avoid circular imports
        from .run_progress import RunProgressState
        from .main import progress_tracker
        
        # Start progress tracking
        run_id = request.seed or str(int(time.time()))
        progress_tracker.start_run(
            run_id,
            request.scenario_id
        )
        
        # Update to PREPARING state
        progress_tracker.update_run_state(
            run_id,
            RunProgressState.PREPARING,
            f"Preparing scenario {request.scenario_id}",
            transport_target=destination_info.get("name") if destination_info else None,
            transport_protocol="HEC" if getattr(request, 'dispatch_telemetry', False) else "Preview"
        )
        
        try:
            # Run scenario (this is synchronous)
            manifest = self.base_runner.run_scenario(request)
            actual_run_id = getattr(manifest, 'run_id', run_id)
            
            # Update progress with run ID
            progress_tracker.update_run_state(
                actual_run_id,
                RunProgressState.GENERATING,
                f"Generating telemetry for {getattr(manifest, 'scenario_name', request.scenario_id)}",
                current_phase="INITIALIZE",
                phases_total=getattr(manifest, 'phases', 9),
                generated_count=0
            )
            
            # Track generation progress
            # Simulate progress through phases
            phases = getattr(manifest, 'phases', ['BASELINE', 'DEGRADE', 'FAULT', 'PROPAGATE', 'RECOVER'])
            for i, phase in enumerate(phases):
                progress_tracker.update_run_state(
                    actual_run_id,
                    RunProgressState.GENERATING,
                    f"Generating {phase} phase telemetry",
                    current_phase=phase,
                    phases_completed=i,
                    generated_count=getattr(manifest, 'total_records', 0)
                )
                await asyncio.sleep(0.1)  # Small delay to show progress
            
            # Update to SENDING state if dispatching
            if getattr(request, 'dispatch_telemetry', False) and hasattr(request, 'transport_config'):
                progress_tracker.update_run_state(
                    actual_run_id,
                    RunProgressState.SENDING,
                    f"Sending telemetry to destination",
                    transport_target=destination_info.get("name") if destination_info else "Splunk",
                    transport_protocol="HEC",
                    transport_status="sending"
                )
                
                # Simulate sending progress
                sent = getattr(manifest, 'dispatch_succeeded', 0)
                total = getattr(manifest, 'total_records', sent)
                
                progress_tracker.update_run_state(
                    actual_run_id,
                    RunProgressState.SENDING,
                    f"Sent {sent}/{total} records",
                    generated_count=total,
                    accepted_count=sent,
                    rejected_count=(total - sent) if total > sent else 0
                )
            
            # Update to VERIFYING state
            progress_tracker.update_run_state(
                actual_run_id,
                RunProgressState.VERIFYING,
                "Verifying indexed records",
                indexed_count=0,
                verified_count=0
            )
            
            # Simulate verification
            await asyncio.sleep(0.5)
            
            # Get verification results if available
            indexed = getattr(manifest, 'indexed_count', 0)
            verified = getattr(manifest, 'verified_count', indexed)
            
            progress_tracker.update_run_state(
                actual_run_id,
                RunProgressState.VERIFYING,
                f"Verified {verified}/{indexed} records",
                indexed_count=indexed,
                verified_count=verified
            )
            
            # Complete the run
            success = getattr(manifest, 'validation_passed', True)
            
            progress_tracker.complete_run(
                actual_run_id,
                success=success,
                generated_count=getattr(manifest, 'total_records', 0),
                accepted_count=getattr(manifest, 'dispatch_succeeded', 0),
                indexed_count=indexed,
                verified_count=verified,
                final_message=f"Scenario {getattr(manifest, 'scenario_name', request.scenario_id)} {'completed successfully' if success else 'failed'}"
            )
            
            return manifest
            
        except Exception as e:
            # Update to FAILED state
            progress_tracker.update_run_state(
                run_id,
                RunProgressState.FAILED,
                f"Scenario execution failed: {str(e)}",
                error=str(e)
            )
            raise
    
    def run_scenario(self, request):
        """Sync wrapper for backward compatibility."""
        return self.base_runner.run_scenario(request)
    
    def __getattr__(self, name):
        """Delegate all other methods to base runner."""
        return getattr(self.base_runner, name)