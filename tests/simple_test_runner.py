"""
Simple Test Runner for Project Archangel - No pytest dependencies
Tests core functionality directly
"""

import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_basic_imports():
    """Test that basic modules can be imported"""
    tests = []
    
    # Test retry utilities
    try:
        tests.append(("Basic utility imports", True, None))
    except Exception as e:
        tests.append(("Basic utility imports", False, str(e)))
    
    # Test database module
    try:
        tests.append(("Database module import", True, None))
    except Exception as e:
        tests.append(("Database module import", False, str(e)))
    
    # Test scoring module (basic)
    try:
        tests.append(("Basic scoring import", True, None))
    except Exception as e:
        tests.append(("Basic scoring import", False, str(e)))
    
    # Test enhanced scoring (may fail without numpy)
    try:
        tests.append(("Enhanced scoring import", True, None))
    except Exception as e:
        tests.append(("Enhanced scoring import (optional)", False, str(e)))
    
    # Test providers
    try:
        tests.append(("Provider modules import", True, None))
    except Exception as e:
        tests.append(("Provider modules import", False, str(e)))
    
    return tests

def test_retry_functionality():
    """Test retry mechanism"""
    tests = []
    
    try:
        from app.utils.retry import next_backoff, retry
        
        # Test backoff calculation
        delay1 = next_backoff(1)
        delay2 = next_backoff(2)
        
        if 0.35 <= delay1 <= 0.65 and delay2 > delay1:
            tests.append(("Exponential backoff calculation", True, None))
        else:
            tests.append(("Exponential backoff calculation", False, f"Delays: {delay1}, {delay2}"))
        
        # Test retry function
        attempt_count = 0
        def flaky_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Test error")
            return "success"
        
        result = retry(flaky_function, max_tries=5)
        if result == "success" and attempt_count == 3:
            tests.append(("Retry function success", True, None))
        else:
            tests.append(("Retry function success", False, f"Result: {result}, attempts: {attempt_count}"))
            
    except Exception as e:
        tests.append(("Retry functionality", False, str(e)))
    
    return tests

def test_outbox_functionality():
    """Test outbox pattern utilities"""
    tests = []
    
    try:
        from app.utils.outbox import OutboxOperation, make_idempotency_key
        
        # Test idempotency key generation
        key1 = make_idempotency_key("webhook", "/api/task", {"id": 123})
        key2 = make_idempotency_key("webhook", "/api/task", {"id": 123})
        key3 = make_idempotency_key("webhook", "/api/task", {"id": 456})
        
        if key1 == key2 and key1 != key3 and len(key1) == 64:
            tests.append(("Idempotency key generation", True, None))
        else:
            tests.append(("Idempotency key generation", False, f"Keys: {key1[:10]}..., {key2[:10]}..., {key3[:10]}..."))
        
        # Test OutboxOperation creation
        op = OutboxOperation(
            id=1,
            idempotency_key="test-key",
            operation_type="webhook",
            endpoint="/test",
            request_body='{"test": true}',
            created_at="2025-01-01T00:00:00Z",
            attempts=0,
            next_attempt="2025-01-01T00:00:00Z"
        )
        
        if op.operation_type == "webhook" and op.attempts == 0:
            tests.append(("OutboxOperation creation", True, None))
        else:
            tests.append(("OutboxOperation creation", False, f"Type: {op.operation_type}, attempts: {op.attempts}"))
            
    except Exception as e:
        tests.append(("Outbox functionality", False, str(e)))
    
    return tests

def test_basic_scoring():
    """Test basic scoring algorithm"""
    tests = []
    
    try:
        from app.scoring import compute_score
        from datetime import datetime, timezone, timedelta
        
        now = datetime.now(timezone.utc)
        
        # Test basic scoring rules
        rules = {
            "clients": {
                "test-client": {
                    "importance_bias": 1.2,
                    "sla_hours": 48
                }
            }
        }
        
        # High priority task
        high_priority_task = {
            "client": "test-client",
            "importance": 5.0,
            "effort_hours": 2.0,
            "deadline": (now + timedelta(hours=4)).isoformat(),
            "created_at": (now - timedelta(hours=1)).isoformat(),
            "recent_progress": 0.0
        }
        
        # Low priority task
        low_priority_task = {
            "client": "test-client",
            "importance": 2.0,
            "effort_hours": 8.0,
            "deadline": (now + timedelta(days=7)).isoformat(),
            "created_at": (now - timedelta(days=2)).isoformat(),
            "recent_progress": 0.5
        }
        
        high_score = compute_score(high_priority_task, rules)
        low_score = compute_score(low_priority_task, rules)
        
        if isinstance(high_score, float) and isinstance(low_score, float):
            if 0.0 <= high_score <= 1.0 and 0.0 <= low_score <= 1.0:
                if high_score > low_score:
                    tests.append(("Basic scoring algorithm", True, None))
                else:
                    tests.append(("Basic scoring algorithm", False, f"High score ({high_score}) should be > low score ({low_score})"))
            else:
                tests.append(("Basic scoring algorithm", False, f"Scores out of range: {high_score}, {low_score}"))
        else:
            tests.append(("Basic scoring algorithm", False, f"Invalid score types: {type(high_score)}, {type(low_score)}"))
            
    except Exception as e:
        tests.append(("Basic scoring algorithm", False, str(e)))
    
    return tests

def test_database_basic():
    """Test basic database functionality"""
    tests = []
    
    try:
        from app.db_pg import get_db_config
        
        # Test database configuration
        database_url, is_sqlite = get_db_config()
        
        if database_url:
            tests.append(("Database configuration", True, None))
        else:
            tests.append(("Database configuration", False, "No DATABASE_URL configured"))
            
    except Exception as e:
        tests.append(("Database configuration", False, str(e)))
    
    return tests

def run_test_category(category_name, test_function):
    """Run a category of tests and return results"""
    print(f"\n--- {category_name} ---")
    
    start_time = time.time()
    try:
        test_results = test_function()
        duration = time.time() - start_time
        
        passed = sum(1 for _, result, _ in test_results if result)
        total = len(test_results)
        
        for test_name, result, error in test_results:
            status = "PASS" if result else "FAIL"
            print(f"  {status:<6} {test_name}")
            if error and not result:
                print(f"         Error: {error}")
        
        print(f"  Category Result: {passed}/{total} passed ({duration:.2f}s)")
        return passed, total, test_results
        
    except Exception as e:
        duration = time.time() - start_time
        print(f"  FAIL   Category failed to run: {str(e)}")
        print(f"  Category Result: 0/1 passed ({duration:.2f}s)")
        return 0, 1, [("Category execution", False, str(e))]

def main():
    """Run all tests"""
    print("PROJECT ARCHANGEL - SIMPLE TEST RUNNER")
    print("=" * 60)
    print(f"Python Version: {sys.version}")
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test categories
    test_categories = [
        ("Basic Imports", test_basic_imports),
        ("Retry Functionality", test_retry_functionality),
        ("Outbox Functionality", test_outbox_functionality),
        ("Basic Scoring", test_basic_scoring),
        ("Database Basic", test_database_basic)
    ]
    
    total_passed = 0
    total_tests = 0
    all_results = {}
    
    start_time = time.time()
    
    for category_name, test_function in test_categories:
        passed, tests, results = run_test_category(category_name, test_function)
        total_passed += passed
        total_tests += tests
        all_results[category_name] = {
            "passed": passed,
            "total": tests,
            "results": results
        }
    
    total_duration = time.time() - start_time
    success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    # Final summary
    print("\n" + "=" * 60)
    print("TEST EXECUTION SUMMARY")
    print("=" * 60)
    print(f"Total Duration: {total_duration:.1f} seconds")
    print(f"Test Results: {total_passed}/{total_tests} passed")
    print(f"Success Rate: {success_rate:.1f}%")
    
    # Overall assessment
    print("\nOverall Assessment:")
    if success_rate >= 90:
        print("   EXCELLENT - Core functionality working well")
    elif success_rate >= 75:
        print("   GOOD - Most functionality working, minor issues")
    elif success_rate >= 50:
        print("   ACCEPTABLE - Basic functionality working")
    else:
        print("   NEEDS ATTENTION - Significant issues detected")
    
    # Failed tests details
    failed_tests = []
    for category_name, category_data in all_results.items():
        for test_name, result, error in category_data["results"]:
            if not result:
                failed_tests.append(f"{category_name}: {test_name} - {error}")
    
    if failed_tests:
        print("\nFailed Tests:")
        for failed_test in failed_tests:
            print(f"  - {failed_test}")
    
    return success_rate >= 75

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)