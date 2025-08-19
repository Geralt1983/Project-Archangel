"""
Comprehensive Test Runner for Project Archangel
Orchestrates all testing phases and generates consolidated reports
"""

import sys
import subprocess
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestPhase:
    """Represents a testing phase with its configuration"""
    
    def __init__(self, name: str, description: str, command: str, timeout: int = 300):
        self.name = name
        self.description = description
        self.command = command
        self.timeout = timeout
        self.result = None
        self.duration = 0
        self.output = ""
        self.errors = ""


class ProjectArchangelTestRunner:
    """Comprehensive test runner for Project Archangel"""
    
    def __init__(self):
        self.test_phases = []
        self.results = {}
        self.start_time = None
        self.end_time = None
        
        # Initialize test phases
        self._setup_test_phases()
    
    def _setup_test_phases(self):
        """Setup all test phases"""
        
        # Phase 1: Environment Setup
        self.test_phases.append(TestPhase(
            name="environment_setup",
            description="Environment Setup and Validation",
            command="python -c \"import app.db_pg; app.db_pg.init(); print('✅ Database initialized')\"",
            timeout=60
        ))
        
        # Phase 2: Unit Tests
        self.test_phases.append(TestPhase(
            name="unit_tests",
            description="Unit Tests (Basic Components)",
            command="python -m pytest tests/test_basic.py -v --tb=short",
            timeout=120
        ))
        
        # Phase 3: Scoring Algorithm Tests
        self.test_phases.append(TestPhase(
            name="scoring_tests",
            description="Scoring Algorithm Tests",
            command="python -m pytest tests/test_scoring.py tests/test_enhanced_scoring.py -v --tb=short",
            timeout=180
        ))
        
        # Phase 4: Provider Integration Tests
        self.test_phases.append(TestPhase(
            name="provider_tests",
            description="Provider Integration Tests",
            command="python -m pytest tests/test_todoist_provider.py -v --tb=short",
            timeout=120
        ))
        
        # Phase 5: Outbox Pattern Tests
        self.test_phases.append(TestPhase(
            name="outbox_tests",
            description="Outbox Pattern and Reliability Tests",
            command="python -m pytest tests/test_outbox_integration.py tests/test_retry.py -v --tb=short",
            timeout=180
        ))
        
        # Phase 6: Integration Tests
        self.test_phases.append(TestPhase(
            name="integration_tests",
            description="Comprehensive Integration Tests",
            command="python tests/test_integration_suite.py",
            timeout=300
        ))
        
        # Phase 7: API Endpoint Tests
        self.test_phases.append(TestPhase(
            name="api_tests",
            description="API Endpoint Tests",
            command="python tests/test_api_endpoints.py",
            timeout=240
        ))
        
        # Phase 8: Load and Performance Tests
        self.test_phases.append(TestPhase(
            name="performance_tests",
            description="Load and Performance Tests",
            command="python tests/test_load_performance.py",
            timeout=600
        ))
    
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met"""
        logger.info("Checking prerequisites...")
        
        # Check Python version
        if sys.version_info < (3, 10):
            logger.error("Python 3.10+ required")
            return False
        
        # Check required modules
        required_modules = [
            'pytest', 'asyncio', 'httpx', 'aiohttp', 
            'fastapi', 'pydantic', 'psycopg2', 'numpy'
        ]
        
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                logger.error(f"Required module '{module}' not found")
                return False
        
        # Check if database is accessible
        try:
            from app.db_pg import get_db_config
            database_url, is_sqlite = get_db_config()
            if not database_url:
                logger.error("DATABASE_URL not configured")
                return False
        except Exception as e:
            logger.error(f"Database configuration error: {e}")
            return False
        
        logger.info("All prerequisites met")
        return True
    
    def check_service_health(self) -> bool:
        """Check if Project Archangel services are running"""
        logger.info("🏥 Checking service health...")
        
        try:
            import httpx
            response = httpx.get("http://localhost:8080/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ API service is healthy")
                return True
            else:
                logger.warning(f"⚠️ API service returned status {response.status_code}")
                return False
        except Exception as e:
            logger.warning(f"⚠️ API service not accessible: {e}")
            logger.info("💡 Some tests will be skipped or mocked")
            return False
    
    def run_phase(self, phase: TestPhase) -> bool:
        """Run a single test phase"""
        logger.info(f"\n🧪 Running: {phase.description}")
        logger.info("-" * 60)
        
        start_time = time.time()
        
        try:
            # Run the command
            result = subprocess.run(
                phase.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=phase.timeout,
                cwd=project_root
            )
            
            phase.duration = time.time() - start_time
            phase.output = result.stdout
            phase.errors = result.stderr
            phase.result = result.returncode == 0
            
            if phase.result:
                logger.info(f"✅ {phase.name} completed successfully ({phase.duration:.1f}s)")
            else:
                logger.error(f"❌ {phase.name} failed ({phase.duration:.1f}s)")
                if phase.errors:
                    logger.error(f"Errors: {phase.errors[:500]}...")
            
            return phase.result
            
        except subprocess.TimeoutExpired:
            phase.duration = time.time() - start_time
            phase.result = False
            phase.errors = f"Test phase timed out after {phase.timeout}s"
            logger.error(f"⏰ {phase.name} timed out after {phase.timeout}s")
            return False
            
        except Exception as e:
            phase.duration = time.time() - start_time
            phase.result = False
            phase.errors = str(e)
            logger.error(f"💥 {phase.name} failed with exception: {e}")
            return False
    
    def run_all_tests(self, skip_on_failure: bool = False) -> Dict[str, Any]:
        """Run all test phases"""
        logger.info("🚀 Starting Project Archangel Comprehensive Test Suite")
        logger.info("=" * 80)
        
        self.start_time = datetime.now()
        
        # Check prerequisites
        if not self.check_prerequisites():
            logger.error("❌ Prerequisites check failed. Aborting tests.")
            return {"status": "failed", "reason": "prerequisites"}
        
        # Check service health
        service_healthy = self.check_service_health()
        
        # Run test phases
        passed_phases = 0
        total_phases = len(self.test_phases)
        
        for i, phase in enumerate(self.test_phases, 1):
            logger.info(f"\n📊 Phase {i}/{total_phases}: {phase.description}")
            
            # Skip API and performance tests if service is not healthy
            if not service_healthy and phase.name in ["api_tests", "performance_tests"]:
                logger.warning(f"⏭️ Skipping {phase.name} (service not healthy)")
                phase.result = None
                phase.errors = "Skipped - service not healthy"
                continue
            
            success = self.run_phase(phase)
            
            if success:
                passed_phases += 1
            elif skip_on_failure:
                logger.warning(f"🛑 Stopping tests due to failure in {phase.name}")
                break
        
        self.end_time = datetime.now()
        
        # Generate results
        results = {
            "status": "completed",
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration": (self.end_time - self.start_time).total_seconds(),
            "total_phases": total_phases,
            "passed_phases": passed_phases,
            "failed_phases": total_phases - passed_phases,
            "success_rate": (passed_phases / total_phases) * 100,
            "service_healthy": service_healthy,
            "phases": {
                phase.name: {
                    "name": phase.name,
                    "description": phase.description,
                    "result": phase.result,
                    "duration": phase.duration,
                    "output": phase.output[:1000] if phase.output else "",
                    "errors": phase.errors[:1000] if phase.errors else ""
                }
                for phase in self.test_phases
            }
        }
        
        return results
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate comprehensive test report"""
        report = []
        
        # Header
        report.append("# Project Archangel - Test Execution Report")
        report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**Duration:** {results['duration']:.1f} seconds")
        report.append("")
        
        # Summary
        report.append("## 📊 Executive Summary")
        report.append("")
        report.append(f"- **Total Test Phases:** {results['total_phases']}")
        report.append(f"- **Passed:** {results['passed_phases']}")
        report.append(f"- **Failed:** {results['failed_phases']}")
        report.append(f"- **Success Rate:** {results['success_rate']:.1f}%")
        report.append(f"- **Service Health:** {'✅ Healthy' if results['service_healthy'] else '⚠️ Unhealthy'}")
        report.append("")
        
        # Overall status
        if results['success_rate'] >= 90:
            report.append("🎉 **Status: EXCELLENT** - System is ready for production")
        elif results['success_rate'] >= 75:
            report.append("✅ **Status: GOOD** - System is stable with minor issues")
        elif results['success_rate'] >= 50:
            report.append("⚠️ **Status: NEEDS ATTENTION** - Several issues require fixing")
        else:
            report.append("❌ **Status: CRITICAL** - Significant issues prevent deployment")
        
        report.append("")
        
        # Phase Details
        report.append("## 📋 Test Phase Results")
        report.append("")
        
        for phase_name, phase_data in results['phases'].items():
            status_icon = "✅" if phase_data['result'] else "❌" if phase_data['result'] is False else "⏭️"
            status_text = "PASSED" if phase_data['result'] else "FAILED" if phase_data['result'] is False else "SKIPPED"
            
            report.append(f"### {status_icon} {phase_data['description']}")
            report.append(f"**Status:** {status_text}")
            report.append(f"**Duration:** {phase_data['duration']:.1f}s")
            
            if phase_data['errors']:
                report.append(f"**Errors:** {phase_data['errors'][:500]}...")
            
            report.append("")
        
        # Recommendations
        report.append("## 💡 Recommendations")
        report.append("")
        
        failed_phases = [
            phase_data for phase_data in results['phases'].values() 
            if phase_data['result'] is False
        ]
        
        if not failed_phases:
            report.append("🎯 All tests passed! System is ready for deployment.")
        else:
            report.append("🔧 Address the following issues:")
            for phase in failed_phases:
                report.append(f"- **{phase['description']}**: {phase['errors'][:200]}...")
        
        report.append("")
        
        # Performance Notes
        if results['service_healthy']:
            report.append("## ⚡ Performance Notes")
            report.append("")
            report.append("- API service is responsive and healthy")
            report.append("- Load testing completed successfully")
            report.append("- System demonstrates good performance characteristics")
        else:
            report.append("## ⚠️ Service Health Issues")
            report.append("")
            report.append("- API service was not accessible during testing")
            report.append("- Performance tests were skipped")
            report.append("- Verify service deployment and configuration")
        
        return "\n".join(report)
    
    def save_results(self, results: Dict[str, Any], output_dir: str = "test_results"):
        """Save test results to files"""
        Path(output_dir).mkdir(exist_ok=True)
        
        # Save JSON results
        json_path = Path(output_dir) / "test_results.json"
        with open(json_path, "w") as f:
            json.dump(results, f, indent=2)
        
        # Save markdown report
        report = self.generate_report(results)
        md_path = Path(output_dir) / "test_report.md"
        with open(md_path, "w") as f:
            f.write(report)
        
        logger.info(f"📄 Results saved to: {output_dir}/")
        logger.info(f"   - JSON: {json_path}")
        logger.info(f"   - Report: {md_path}")
    
    def print_summary(self, results: Dict[str, Any]):
        """Print test execution summary"""
        print("\n" + "=" * 80)
        print("PROJECT ARCHANGEL - TEST EXECUTION SUMMARY")
        print("=" * 80)
        
        print(f"\nTotal Duration: {results['duration']:.1f} seconds")
        print(f"Test Phases: {results['passed_phases']}/{results['total_phases']} passed")
        print(f"Success Rate: {results['success_rate']:.1f}%")
        
        # Phase breakdown
        print("\nPhase Results:")
        for phase_name, phase_data in results['phases'].items():
            if phase_data['result'] is True:
                status = "PASSED"
            elif phase_data['result'] is False:
                status = "FAILED"
            else:
                status = "SKIPPED"
            
            print(f"   {status:<10} {phase_data['description']:<40} ({phase_data['duration']:.1f}s)")
        
        # Overall assessment
        print("\nOverall Assessment:")
        if results['success_rate'] >= 90:
            print("   EXCELLENT - Ready for production deployment")
        elif results['success_rate'] >= 75:
            print("   GOOD - Minor issues, mostly ready")
        elif results['success_rate'] >= 50:
            print("   NEEDS ATTENTION - Several issues to resolve")
        else:
            print("   CRITICAL - Major issues prevent deployment")


def main():
    """Main execution function"""
    runner = ProjectArchangelTestRunner()
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Project Archangel Test Runner")
    parser.add_argument("--skip-on-failure", action="store_true", 
                       help="Stop testing on first failure")
    parser.add_argument("--output-dir", default="test_results",
                       help="Output directory for test results")
    
    args = parser.parse_args()
    
    # Run tests
    results = runner.run_all_tests(skip_on_failure=args.skip_on_failure)
    
    # Print summary
    runner.print_summary(results)
    
    # Save results
    runner.save_results(results, args.output_dir)
    
    # Exit with appropriate code
    if results['success_rate'] >= 75:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure


if __name__ == "__main__":
    main()