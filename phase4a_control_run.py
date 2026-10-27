#!/usr/bin/env python3
"""
PulseForge Phase 4A - Live Control Run
Restores and verifies baseline functionality with cisco_aci_microburst scenario.
"""

import sys
import os
import json
import time
import asyncio
import subprocess
import requests
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.absolute()
BACKEND_DIR = BASE_DIR / "backend"

# Set environment
os.environ['PULSEFORGE_LAB_HEC_TOKEN'] = "1379bbf9-5535-48d8-ab4e-b20e2ff6deee"

# Add paths
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BASE_DIR / "netspout" / "bin"))
sys.path.insert(0, str(BASE_DIR / "src"))

class Phase4AControlRun:
    def __init__(self):
        self.run_id = f"NS-{datetime.now().strftime('%Y%m%d')}-{int(time.time()) % 1000000:06x}"
        self.scenario_id = "cisco_aci_microburst"
        self.destination_id = "codex_local_lab"
        self.backend_url = "http://localhost:8000"
        self.backend_process = None
        
        # Splunk config
        self.splunk_url = "https://localhost:18000"
        self.splunk_api = "https://localhost:18089"
        self.hec_url = "https://localhost:18088"
        self.splunk_auth = ("admin", "Lab-Aa1!Ko2wmmP0nL22v8w2iQvxLDNYWxFMI5Qm")
        
        self.results = {
            "phase4a_control_run": True,
            "run_id": self.run_id,
            "scenario_id": self.scenario_id,
            "destination_id": self.destination_id,
            "start_time": datetime.now().isoformat(),
            "tests": {}
        }
    
    def print_header(self, text):
        print(f"\n{'='*60}")
        print(f"🔍 {text}")
        print(f"{'='*60}")
    
    def record_test(self, name, status, details=None, evidence=None):
        self.results['tests'][name] = {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "details": details,
            "evidence": evidence
        }
        
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {name}: {status}")
        if details:
            print(f"   {details}")
        
        return status == "PASS"
    
    # === TEST 1: Check Splunk Lab ===
    def test_splunk_lab(self):
        self.print_header("1. Splunk Docker Lab Verification")
        
        # Check Docker container
        try:
            result = subprocess.run(
                ["docker", "ps", "-f", "name=pf-native-lab", "--format", "{{.Names}} {{.Status}}"],
                capture_output=True, text=True, timeout=5
            )
            
            if "pf-native-lab" in result.stdout and "Up" in result.stdout:
                return self.record_test(
                    "Docker Container", 
                    "PASS",
                    "pf-native-lab running and healthy",
                    result.stdout.strip()
                )
            else:
                return self.record_test(
                    "Docker Container",
                    "FAIL",
                    f"Container not running or unhealthy: {result.stdout.strip()}"
                )
        except Exception as e:
            return self.record_test(
                "Docker Container",
                "FAIL",
                f"Error checking Docker: {str(e)}"
            )
    
    # === TEST 2: Check HEC Connectivity ===
    def test_hec_connectivity(self):
        self.print_header("2. HEC Connectivity Verification")
        
        try:
            response = requests.post(
                f"{self.hec_url}/services/collector",
                headers={"Authorization": f"Splunk {os.environ['PULSEFORGE_LAB_HEC_TOKEN']}"},
                json={
                    "event": f"Phase 4A control run connectivity test - {self.run_id}",
                    "sourcetype": "phase4a_test",
                    "index": "idx_ta_ise_test"
                },
                verify=False,
                timeout=5
            )
            
            if response.status_code == 200:
                return self.record_test(
                    "HEC Connectivity",
                    "PASS",
                    f"HEC accepts events (HTTP {response.status_code})",
                    response.json()
                )
            else:
                return self.record_test(
                    "HEC Connectivity",
                    "FAIL",
                    f"HEC rejected event: HTTP {response.status_code}: {response.text}"
                )
        except Exception as e:
            return self.record_test(
                "HEC Connectivity",
                "FAIL",
                f"Error connecting to HEC: {str(e)}"
            )
    
    # === TEST 3: Check Splunk REST API ===
    def test_splunk_api(self):
        self.print_header("3. Splunk REST API Verification")
        
        try:
            response = requests.get(
                f"{self.splunk_api}/services/server/info",
                auth=self.splunk_auth,
                verify=False,
                timeout=5
            )
            
            if response.status_code == 200:
                # Parse XML response
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.text)
                
                version = "unknown"
                build = "unknown"
                
                for entry in root.findall(".//entry"):
                    content = entry.find("content")
                    if content is not None:
                        dict_elem = content.find("dict")
                        if dict_elem is not None:
                            for key in dict_elem.findall("key"):
                                if key.get("name") == "version":
                                    version = key.text
                                elif key.get("name") == "build":
                                    build = key.text
                
                return self.record_test(
                    "Splunk REST API",
                    "PASS",
                    f"Splunk {version} (build {build})",
                    f"Version: {version}, Build: {build}"
                )
            else:
                return self.record_test(
                    "Splunk REST API",
                    "FAIL",
                    f"API returned HTTP {response.status_code}"
                )
        except Exception as e:
            return self.record_test(
                "Splunk REST API",
                "FAIL",
                f"Error connecting to Splunk API: {str(e)}"
            )
    
    # === TEST 4: Start Backend Server ===
    def start_backend_server(self):
        self.print_header("4. Backend Server Startup")
        
        # Check if backend is already running
        try:
            response = requests.get(f"{self.backend_url}/docs", timeout=2)
            if response.status_code == 200:
                return self.record_test(
                    "Backend Server",
                    "PASS",
                    "Already running",
                    f"HTTP {response.status_code}"
                )
        except:
            pass  # Not running, need to start it
        
        # Start backend server
        try:
            env = os.environ.copy()
            env['PYTHONPATH'] = ":".join([
                str(BASE_DIR / "backend"),
                str(BASE_DIR / "netspout" / "bin"),
                str(BASE_DIR / "src"),
                env.get('PYTHONPATH', '')
            ])
            
            self.backend_process = subprocess.Popen(
                [
                    sys.executable, "-m", "uvicorn", "app.main:app",
                    "--host", "0.0.0.0",
                    "--port", "8000",
                    "--reload"
                ],
                cwd=str(BACKEND_DIR),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for server to start
            for _ in range(30):  # 30 second timeout
                time.sleep(1)
                try:
                    response = requests.get(f"{self.backend_url}/docs", timeout=1)
                    if response.status_code == 200:
                        return self.record_test(
                            "Backend Server",
                            "PASS",
                            "Started successfully",
                            f"PID: {self.backend_process.pid}"
                        )
                except:
                    continue
            
            # If we get here, server didn't start
            stdout, stderr = self.backend_process.communicate(timeout=2)
            return self.record_test(
                "Backend Server",
                "FAIL",
                "Failed to start within 30 seconds",
                f"STDOUT: {stdout[:500]}\nSTDERR: {stderr[:500]}"
            )
            
        except Exception as e:
            return self.record_test(
                "Backend Server",
                "FAIL",
                f"Error starting backend: {str(e)}"
            )
    
    # === TEST 5: Verify Scenario Exists ===
    def test_scenario_exists(self):
        self.print_header("5. Scenario Verification")
        
        try:
            # Try catalog instance first
            from app.catalog import catalog_instance
            scenario = catalog_instance.get_scenario(self.scenario_id)
            
            if scenario:
                details = {
                    "name": scenario.get('name', 'N/A'),
                    "maturity": scenario.get('maturity', 'N/A'),
                    "sourcetypes": scenario.get('sourcetypes', []),
                    "description": scenario.get('description', '')[:100] + "..."
                }
                
                return self.record_test(
                    "Scenario Exists",
                    "PASS",
                    f"Found: {scenario.get('name', 'N/A')}",
                    details
                )
            else:
                return self.record_test(
                    "Scenario Exists",
                    "FAIL",
                    f"Scenario '{self.scenario_id}' not found in catalog"
                )
                
        except Exception as e:
            return self.record_test(
                "Scenario Exists",
                "FAIL",
                f"Error accessing catalog: {str(e)}"
            )
    
    # === TEST 6: Preview Scenario ===
    def test_scenario_preview(self):
        self.print_header("6. Scenario Preview Test")
        
        try:
            response = requests.post(
                f"{self.backend_url}/api/acceptance/preview/{self.scenario_id}",
                json={},
                timeout=30
            )
            
            if response.status_code == 200:
                preview = response.json()
                events = preview.get('events', [])
                event_count = len(events)
                sourcetype_counts = {}
                
                for event in events:
                    st = event.get('sourcetype', 'unknown')
                    sourcetype_counts[st] = sourcetype_counts.get(st, 0) + 1
                
                details = {
                    "event_count": event_count,
                    "sourcetype_distribution": sourcetype_counts,
                    "dispatch_enabled": preview.get('dispatch_enabled', False)
                }
                
                return self.record_test(
                    "Scenario Preview",
                    "PASS",
                    f"Generated {event_count} preview events",
                    details
                )
            else:
                return self.record_test(
                    "Scenario Preview",
                    "FAIL",
                    f"HTTP {response.status_code}: {response.text[:200]}"
                )
                
        except Exception as e:
            return self.record_test(
                "Scenario Preview",
                "FAIL",
                f"Error during preview: {str(e)}"
            )
    
    # === TEST 7: Execute Scenario ===
    def test_scenario_execution(self):
        self.print_header("7. Scenario Execution Test")
        
        try:
            payload = {
                "scenario_id": self.scenario_id,
                "destination_id": self.destination_id,
                "seed": 42  # Deterministic seed like Codex used
            }
            
            response = requests.post(
                f"{self.backend_url}/api/scenarios/run-with-destination",
                json=payload,
                timeout=60  # 60 second timeout for execution
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Record detailed results
                execution_details = {
                    "backend_run_id": result.get('run_id', 'unknown'),
                    "generated": result.get('total_events_generated', 0),
                    "accepted": result.get('dispatch_succeeded', 0),
                    "failed": result.get('dispatch_failed', 0),
                    "observed": result.get('observed_count', 0),
                    "observation_status": result.get('observation_status', 'unknown'),
                    "errors": result.get('errors', [])
                }
                
                # Store for later verification
                self.execution_result = result
                
                return self.record_test(
                    "Scenario Execution",
                    "PASS",
                    f"Run completed: {execution_details['generated']} generated, {execution_details['accepted']} accepted",
                    execution_details
                )
            else:
                return self.record_test(
                    "Scenario Execution",
                    "FAIL",
                    f"HTTP {response.status_code}: {response.text[:200]}"
                )
                
        except Exception as e:
            return self.record_test(
                "Scenario Execution",
                "FAIL",
                f"Error during execution: {str(e)}"
            )
    
    # === TEST 8: Verify Splunk Indexing ===
    def test_splunk_indexing(self):
        self.print_header("8. Splunk Indexing Verification")
        
        if not hasattr(self, 'execution_result'):
            return self.record_test(
                "Splunk Indexing",
                "BLOCKED",
                "No execution result available"
            )
        
        run_id = self.execution_result.get('run_id', self.run_id)
        
        try:
            # Wait a moment for events to index
            time.sleep(3)
            
            # Test event search
            event_search = f'search index=idx_network_ops netspout_run_id="{run_id}" earliest=-5m latest=now | head 5'
            
            response = requests.post(
                f"{self.splunk_api}/services/search/jobs",
                auth=self.splunk_auth,
                data={"search": event_search, "exec_mode": "oneshot", "output_mode": "json"},
                verify=False,
                timeout=10
            )
            
            if response.status_code == 201:
                # Parse results
                try:
                    results = response.json()
                    event_count = len(results.get('results', []))
                    
                    event_details = {
                        "search_job_created": True,
                        "event_count_found": event_count,
                        "search_sid": response.headers.get('sid', 'unknown')
                    }
                    
                    return self.record_test(
                        "Event Indexing",
                        "PASS" if event_count > 0 else "PARTIAL",
                        f"Found {event_count} events",
                        event_details
                    )
                except json.JSONDecodeError:
                    return self.record_test(
                        "Event Indexing",
                        "PARTIAL",
                        "Search job created but couldn't parse results"
                    )
            else:
                return self.record_test(
                    "Event Indexing",
                    "FAIL",
                    f"Search API returned HTTP {response.status_code}"
                )
                
        except Exception as e:
            return self.record_test(
                "Event Indexing",
                "FAIL",
                f"Error verifying indexing: {str(e)}"
            )
    
    # === TEST 9: Verify Metrics Indexing ===
    def test_metrics_indexing(self):
        self.print_header("9. Metrics Indexing Verification")
        
        if not hasattr(self, 'execution_result'):
            return self.record_test(
                "Metrics Indexing",
                "BLOCKED",
                "No execution result available"
            )
        
        run_id = self.execution_result.get('run_id', self.run_id)
        
        try:
            # Test metrics search
            metrics_search = f'| mstats count WHERE index=idx_performance_metrics netspout_run_id="{run_id}" earliest=-5m latest=now'
            
            response = requests.post(
                f"{self.splunk_api}/services/search/jobs",
                auth=self.splunk_auth,
                data={"search": metrics_search, "exec_mode": "oneshot", "output_mode": "json"},
                verify=False,
                timeout=10
            )
            
            if response.status_code == 201:
                metrics_details = {
                    "metrics_search_job_created": True,
                    "search_sid": response.headers.get('sid', 'unknown')
                }
                
                # Note: We can't easily parse mstats JSON without more complex parsing
                return self.record_test(
                    "Metrics Indexing",
                    "PARTIAL",
                    "Metrics search job created",
                    metrics_details
                )
            else:
                return self.record_test(
                    "Metrics Indexing",
                    "FAIL",
                    f"Metrics search API returned HTTP {response.status_code}"
                )
                
        except Exception as e:
            return self.record_test(
                "Metrics Indexing",
                "FAIL",
                f"Error verifying metrics: {str(e)}"
            )
    
    # === TEST 10: Dashboard Deployment ===
    def test_dashboard_deployment(self):
        self.print_header("10. Dashboard Deployment Test")
        
        if not hasattr(self, 'execution_result'):
            return self.record_test(
                "Dashboard Deployment",
                "BLOCKED",
                "No execution result available"
            )
        
        run_id = self.execution_result.get('run_id', self.run_id)
        
        try:
            payload = {
                "destination_id": self.destination_id
            }
            
            response = requests.post(
                f"{self.backend_url}/api/acceptance/dashboards/{run_id}",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                dashboard_result = response.json()
                
                dashboard_details = {
                    "dashboard_id": dashboard_result.get('dashboard_id', 'unknown'),
                    "status": dashboard_result.get('status', 'unknown'),
                    "url": dashboard_result.get('url', ''),
                    "deployment_successful": True
                }
                
                return self.record_test(
                    "Dashboard Deployment",
                    "PASS",
                    f"Dashboard {dashboard_details['dashboard_id']} created",
                    dashboard_details
                )
            else:
                return self.record_test(
                    "Dashboard Deployment",
                    "FAIL",
                    f"HTTP {response.status_code}: {response.text[:200]}"
                )
                
        except Exception as e:
            return self.record_test(
                "Dashboard Deployment",
                "FAIL",
                f"Error deploying dashboard: {str(e)}"
            )
    
    # === RUN ALL TESTS ===
    def run_all_tests(self):
        print("\n" + "="*60)
        print("🚀 PULSEFORGE PHASE 4A - LIVE CONTROL RUN")
        print("="*60)
        print(f"Run ID: {self.run_id}")
        print(f"Scenario: {self.scenario_id}")
        print(f"Destination: {self.destination_id}")
        print(f"Start Time: {self.results['start_time']}")
        print("="*60)
        
        all_passed = True
        
        # Run infrastructure tests
        if not self.test_splunk_lab():
            all_passed = False
            print("❌ Splunk lab test failed - stopping")
            return False
        
        if not self.test_hec_connectivity():
            all_passed = False
            print("❌ HEC connectivity test failed - stopping")
            return False
        
        if not self.test_splunk_api():
            all_passed = False
            print("⚠️  Splunk API test failed but continuing")
        
        # Start backend and run scenario tests
        if not self.start_backend_server():
            all_passed = False
            print("❌ Backend server failed to start - stopping")
            return False
        
        # Give backend a moment to fully initialize
        time.sleep(2)
        
        if not self.test_scenario_exists():
            all_passed = False
            print("❌ Scenario not found - stopping")
            return False
        
        if not self.test_scenario_preview():
            all_passed = False
            print("⚠️  Scenario preview test failed but continuing")
        
        if not self.test_scenario_execution():
            all_passed = False
            print("❌ Scenario execution failed - stopping")
            return False
        
        # Verify Splunk results
        if not self.test_splunk_indexing():
            all_passed = False
            print("⚠️  Event indexing verification issue")
        
        if not self.test_metrics_indexing():
            all_passed = False
            print("⚠️  Metrics indexing verification issue")
        
        if not self.test_dashboard_deployment():
            all_passed = False
            print("⚠️  Dashboard deployment issue")
        
        # Generate final report
        self.generate_final_report(all_passed)
        
        # Cleanup
        self.cleanup()
        
        return all_passed
    
    def generate_final_report(self, all_passed):
        self.print_header("📊 CONTROL RUN SUMMARY")
        
        # Count test results
        status_counts = {"PASS": 0, "FAIL": 0, "PARTIAL": 0, "BLOCKED": 0}
        for test_name, test_result in self.results['tests'].items():
            status = test_result['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"\nTest Results:")
        for status, count in status_counts.items():
            if count > 0:
                print(f"  {status}: {count}")
        
        self.results['end_time'] = datetime.now().isoformat()
        self.results['overall_status'] = "PASS" if all_passed else "FAIL"
        self.results['test_summary'] = status_counts
        
        # Save results
        verification_dir = BASE_DIR / "docs" / "verification"
        verification_dir.mkdir(parents=True, exist_ok=True)
        
        results_file = verification_dir / f"phase4a_control_run_{self.run_id}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        # Print summary
        print(f"\n{'='*60}")
        if all_passed:
            print("🎉 CONTROL RUN: SUCCESS")
            print(f"   Baseline functionality RESTORED and VERIFIED")
        else:
            print("⚠️  CONTROL RUN: PARTIAL SUCCESS WITH ISSUES")
            print(f"   Some tests failed - check details above")
        
        print(f"\n📁 Full results saved to: {results_file}")
        print(f"📋 Run ID: {self.run_id}")
        
        # Show key findings
        print(f"\n🔍 Key Findings:")
        if hasattr(self, 'execution_result'):
            exec_result = self.execution_result
            print(f"   - Generated: {exec_result.get('total_events_generated', 0)} records")
            print(f"   - Accepted: {exec_result.get('dispatch_succeeded', 0)} by HEC")
            print(f"   - Observed: {exec_result.get('observed_count', 0)} in Splunk")
        
        return results_file
    
    def cleanup(self):
        """Clean up backend process."""
        if self.backend_process:
            try:
                self.backend_process.terminate()
                self.backend_process.wait(timeout=5)
                print("\n✅ Backend server stopped")
            except:
                try:
                    self.backend_process.kill()
                    self.backend_process.wait(timeout=2)
                except:
                    pass

def main():
    """Run the Phase 4A control run."""
    print("Preparing Phase 4A Control Run...")
    
    # Check if we're in the right directory
    if not (BASE_DIR / "backend").exists():
        print(f"❌ ERROR: Backend directory not found at {BASE_DIR / 'backend'}")
        print(f"   Current directory: {BASE_DIR}")
        return 1
    
    # Run the control run
    control_run = Phase4AControlRun()
    success = control_run.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())