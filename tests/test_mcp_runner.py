"""
Test Runner for MCP Integration Test Suite
Provides comprehensive test execution and reporting for MCP integration
"""

import pytest
import sys
import os
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class MCPTestRunner:
    """Test runner for MCP integration tests"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
    
    def run_unit_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """Run unit tests for MCP components"""
        print("=" * 80)
        print("MCP INTEGRATION UNIT TESTS")
        print("=" * 80)
        
        unit_test_files = [
            "tests/test_mcp_bridge.py",
            "tests/test_enhanced_tasks.py"
        ]
        
        args = ["-v"] if verbose else ["-q"]
        args.extend(["--tb=short", "-x"])  # Stop on first failure
        args.extend(unit_test_files)
        
        start_time = time.time()
        exit_code = pytest.main(args)
        duration = time.time() - start_time
        
        result = {
            "exit_code": exit_code,
            "duration": duration,
            "status": "PASSED" if exit_code == 0 else "FAILED"
        }
        
        self.test_results["unit_tests"] = result
        return result
    
    def run_integration_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """Run integration tests for MCP workflow"""
        print("\n" + "=" * 80)
        print("MCP INTEGRATION WORKFLOW TESTS")
        print("=" * 80)
        
        args = ["-v"] if verbose else ["-q"]
        args.extend([
            "--tb=short",
            "-m", "integration",
            "tests/test_mcp_integration.py"
        ])
        
        start_time = time.time()
        exit_code = pytest.main(args)
        duration = time.time() - start_time
        
        result = {
            "exit_code": exit_code,
            "duration": duration,
            "status": "PASSED" if exit_code == 0 else "FAILED"
        }
        
        self.test_results["integration_tests"] = result
        return result
    
    def run_performance_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """Run performance tests for MCP integration"""
        print("\n" + "=" * 80)
        print("MCP INTEGRATION PERFORMANCE TESTS")
        print("=" * 80)
        
        args = ["-v"] if verbose else ["-q"]
        args.extend([
            "--tb=short",
            "-m", "performance",
            "tests/test_mcp_performance.py"
        ])
        
        start_time = time.time()
        exit_code = pytest.main(args)
        duration = time.time() - start_time
        
        result = {
            "exit_code": exit_code,
            "duration": duration,
            "status": "PASSED" if exit_code == 0 else "FAILED"
        }
        
        self.test_results["performance_tests"] = result
        return result
    
    def run_all_tests(self, skip_performance: bool = False, verbose: bool = True) -> Dict[str, Any]:
        """Run all MCP integration tests"""
        print("🚀 Starting MCP Integration Test Suite")
        print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        self.start_time = time.time()
        
        # Run test suites in order
        try:
            # Unit tests first (fastest)
            unit_result = self.run_unit_tests(verbose)
            
            # Integration tests (medium speed)
            if unit_result["status"] == "PASSED":
                integration_result = self.run_integration_tests(verbose)
            else:
                print("⚠️  Skipping integration tests due to unit test failures")
                integration_result = {"status": "SKIPPED", "reason": "unit_test_failure"}
            
            # Performance tests (slowest, optional)
            if not skip_performance and integration_result.get("status") == "PASSED":
                performance_result = self.run_performance_tests(verbose)
            else:
                if skip_performance:
                    print("⚠️  Skipping performance tests (--skip-performance)")
                else:
                    print("⚠️  Skipping performance tests due to integration test failures")
                performance_result = {"status": "SKIPPED", "reason": "skipped_or_failure"}
            
        except KeyboardInterrupt:
            print("\n❌ Test execution interrupted by user")
            return {"status": "INTERRUPTED"}
        
        self.end_time = time.time()
        
        # Generate summary report
        return self._generate_summary_report()
    
    def _generate_summary_report(self) -> Dict[str, Any]:
        """Generate comprehensive test summary report"""
        total_duration = self.end_time - self.start_time if self.end_time and self.start_time else 0
        
        print("\n" + "=" * 80)
        print("MCP INTEGRATION TEST SUMMARY")
        print("=" * 80)
        
        # Count results
        passed = sum(1 for result in self.test_results.values() 
                    if result.get("status") == "PASSED")
        failed = sum(1 for result in self.test_results.values() 
                    if result.get("status") == "FAILED")
        skipped = sum(1 for result in self.test_results.values() 
                     if result.get("status") == "SKIPPED")
        
        # Print detailed results
        for test_type, result in self.test_results.items():
            status_emoji = {
                "PASSED": "✅",
                "FAILED": "❌", 
                "SKIPPED": "⏭️"
            }.get(result.get("status"), "❓")
            
            duration_str = f" ({result.get('duration', 0):.2f}s)" if result.get('duration') else ""
            print(f"{status_emoji} {test_type.replace('_', ' ').title()}: {result.get('status')}{duration_str}")
            
            if result.get("reason"):
                print(f"   Reason: {result['reason']}")
        
        print(f"\n📊 Results: {passed} passed, {failed} failed, {skipped} skipped")
        print(f"⏱️  Total time: {total_duration:.2f}s")
        
        # Overall status
        if failed > 0:
            overall_status = "FAILED"
            print("❌ Overall Status: FAILED")
        elif passed > 0:
            overall_status = "PASSED"
            print("✅ Overall Status: PASSED")
        else:
            overall_status = "NO_TESTS"
            print("⚠️  Overall Status: NO TESTS RUN")
        
        # Recommendations
        print("\n📋 Recommendations:")
        if failed > 0:
            print("  - Fix failing tests before deploying MCP integration")
            print("  - Check logs for detailed error information")
        elif skipped > 0:
            print("  - Consider running skipped tests for complete validation")
        else:
            print("  - MCP integration is ready for deployment")
            print("  - Consider running performance tests regularly")
        
        return {
            "overall_status": overall_status,
            "total_duration": total_duration,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "test_results": self.test_results,
            "timestamp": datetime.now().isoformat()
        }
    
    def save_results(self, filepath: str = None) -> str:
        """Save test results to JSON file"""
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"mcp_test_results_{timestamp}.json"
        
        results = {
            "test_suite": "MCP Integration Tests",
            "timestamp": datetime.now().isoformat(),
            "total_duration": self.end_time - self.start_time if self.end_time and self.start_time else 0,
            "results": self.test_results
        }
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"📄 Test results saved to: {filepath}")
        return filepath


def run_quick_smoke_test() -> bool:
    """Run quick smoke test to verify basic MCP functionality"""
    print("🔥 Running MCP Integration Smoke Test...")
    
    try:
        # Import key components to verify they load
        from app.integrations.mcp_bridge import MCPBridge
        from app.services.enhanced_tasks import EnhancedTaskService
        print("✅ MCP components import successfully")
        
        # Run minimal test
        args = [
            "-v",
            "--tb=short",
            "-k", "test_config_loading_success",
            "tests/test_mcp_bridge.py"
        ]
        
        exit_code = pytest.main(args)
        
        if exit_code == 0:
            print("✅ Smoke test PASSED - MCP integration basic functionality works")
            return True
        else:
            print("❌ Smoke test FAILED - Check MCP integration setup")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Smoke test error: {e}")
        return False


def check_test_environment() -> Dict[str, Any]:
    """Check test environment prerequisites"""
    print("🔍 Checking Test Environment...")
    
    checks = {}
    
    # Check Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    checks["python_version"] = {
        "value": python_version,
        "status": "PASS" if sys.version_info >= (3, 8) else "FAIL"
    }
    
    # Check required packages
    required_packages = ["pytest", "pytest-asyncio", "httpx", "structlog", "pydantic"]
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            checks[f"package_{package}"] = {"status": "PASS"}
        except ImportError:
            checks[f"package_{package}"] = {"status": "FAIL", "error": "Not installed"}
    
    # Check test files exist
    test_files = [
        "tests/test_mcp_bridge.py",
        "tests/test_enhanced_tasks.py", 
        "tests/test_mcp_integration.py",
        "tests/fixtures/mcp_responses.py"
    ]
    
    for test_file in test_files:
        file_path = project_root / test_file
        checks[f"file_{test_file}"] = {
            "status": "PASS" if file_path.exists() else "FAIL"
        }
    
    # Check database setup
    try:
        from app.db_pg import init
        checks["database_setup"] = {"status": "PASS"}
    except Exception as e:
        checks["database_setup"] = {"status": "FAIL", "error": str(e)}
    
    # Print results
    failed_checks = [name for name, check in checks.items() if check["status"] == "FAIL"]
    
    if failed_checks:
        print("❌ Environment check FAILED:")
        for check_name in failed_checks:
            error = checks[check_name].get("error", "Unknown error")
            print(f"  - {check_name}: {error}")
        return {"status": "FAIL", "checks": checks}
    else:
        print("✅ Environment check PASSED")
        return {"status": "PASS", "checks": checks}


def main():
    """Main entry point for MCP test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Integration Test Runner")
    parser.add_argument("--smoke", action="store_true", help="Run quick smoke test only")
    parser.add_argument("--skip-performance", action="store_true", help="Skip performance tests")
    parser.add_argument("--unit-only", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration-only", action="store_true", help="Run integration tests only")
    parser.add_argument("--performance-only", action="store_true", help="Run performance tests only")
    parser.add_argument("--quiet", action="store_true", help="Quiet output")
    parser.add_argument("--save-results", type=str, help="Save results to file")
    parser.add_argument("--check-env", action="store_true", help="Check environment only")
    
    args = parser.parse_args()
    
    # Check environment if requested
    if args.check_env:
        check_result = check_test_environment()
        return 0 if check_result["status"] == "PASS" else 1
    
    # Run smoke test if requested
    if args.smoke:
        return 0 if run_quick_smoke_test() else 1
    
    # Check environment before running tests
    env_check = check_test_environment()
    if env_check["status"] == "FAIL":
        print("❌ Environment check failed. Please fix issues before running tests.")
        return 1
    
    runner = MCPTestRunner()
    verbose = not args.quiet
    
    try:
        if args.unit_only:
            result = runner.run_unit_tests(verbose)
        elif args.integration_only:
            result = runner.run_integration_tests(verbose)
        elif args.performance_only:
            result = runner.run_performance_tests(verbose)
        else:
            result = runner.run_all_tests(skip_performance=args.skip_performance, verbose=verbose)
        
        # Save results if requested
        if args.save_results:
            runner.save_results(args.save_results)
        
        # Return appropriate exit code
        if result.get("overall_status") == "PASSED":
            return 0
        elif result.get("overall_status") == "INTERRUPTED":
            return 130  # Ctrl+C
        else:
            return 1
            
    except Exception as e:
        print(f"❌ Test runner error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())